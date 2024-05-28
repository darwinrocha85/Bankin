package com.rocha.bankinc.repository;

import com.rocha.bankinc.entity.CardCredit;
import com.rocha.bankinc.entity.Person;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;


@Repository
public interface CardCreditRepository extends JpaRepository<CardCredit, Long>{

    CardCredit findByCardId(@Param("cardId") String codeProduct);


}
